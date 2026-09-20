/* =============================================================================
 * samples.js — Synthetic demonstration cases, AY 2026-27
 * -----------------------------------------------------------------------------
 * Every figure and name is invented. Each case drives a different path through
 * section 44AB as it stands for FY 2025-26, and each `expect` was worked out by
 * hand from the provisions before the engine was run — the QA suite asserts the
 * engine against it.
 * ========================================================================== */

(function (global) {
  'use strict';

  var TAS = global.TAS || (global.TAS = {});

  function base(o) {
    var b = {
      clientName: '', pan: '', assessmentYear: 'AY 2026-27',
      constitution: 'individual', residentialStatus: 'resident', nature: 'business', professionCategory: '',
      turnover: '', turnoverNonBanking: '', totalReceipts: '', cashReceipts: '', totalPayments: '', cashPayments: '',
      profit: '', totalIncome: '', exemptionOption: 'new-regime',
      bar44AD: '', prior44AD: '', declarePresumptive: '',
      flags: [], preparedBy: '', reviewedBy: ''
    };
    Object.keys(o).forEach(function (k) { b[k] = o[k]; });
    return b;
  }

  var cases = [
    {
      id: 'case-01', expect: 'NOT APPLICABLE', ground: null,
      title: 'Small trader within every limit',
      path: 'Turnover ₹60 lakh: neither the ₹1 crore limit nor the s. 44AD ceiling is reached, and profit meets the deemed rate.',
      input: base({ clientName: 'Meridian Traders (sample)', turnover: '6000000',
        totalReceipts: '6000000', cashReceipts: '180000', totalPayments: '5200000', cashPayments: '140000',
        profit: '620000', totalIncome: '655000', bar44AD: 'no', preparedBy: 'Article Assistant (sample)' })
    },
    {
      id: 'case-02', expect: 'APPLICABLE', ground: 's. 44AB(a)',
      title: 'Trader above ₹2 crore with cash above 5%',
      path: 'Cash receipts 10% — the ₹1 crore limit applies and the s. 44AD ceiling stays at ₹2 crore. Turnover ₹2.5 crore exceeds both.',
      input: base({ clientName: 'Kaveri Hardware Stores (sample)', turnover: '25000000',
        totalReceipts: '25000000', cashReceipts: '2500000', totalPayments: '22000000', cashPayments: '2000000',
        profit: '2200000', totalIncome: '2250000', bar44AD: 'no' })
    },
    {
      id: 'case-03', expect: 'NOT APPLICABLE', ground: null,
      title: 'Firm relying on the ₹10 crore limit',
      path: 'Both cash limbs within 5%, so the ₹10 crore limit applies. Turnover ₹8.2 crore — headroom ₹1.8 crore.',
      input: base({ clientName: 'Sunview Components & Co. (sample)', constitution: 'firm', turnover: '82000000',
        totalReceipts: '82000000', cashReceipts: '2900000', totalPayments: '76000000', cashPayments: '2600000',
        profit: '5400000', totalIncome: '5400000', bar44AD: 'no' })
    },
    {
      id: 'case-04', expect: 'NOT APPLICABLE', ground: 'First proviso',
      title: 'Trader at ₹2.5 crore declaring under s. 44AD',
      path: 'Turnover exceeds ₹1 crore and cash payments exceed 5%, but cash receipts are within 5% of turnover — ₹3 crore ceiling. Income declared under s. 44AD(1): s. 44AB does not apply (Finance Act 2023).',
      input: base({ clientName: 'Anand Distributors (sample)', turnover: '25000000', turnoverNonBanking: '1000000',
        totalReceipts: '25000000', cashReceipts: '1000000', totalPayments: '23000000', cashPayments: '3000000',
        profit: '1800000', totalIncome: '1800000', bar44AD: 'no', declarePresumptive: 'yes' })
    },
    {
      id: 'case-05', expect: 'NOT APPLICABLE', ground: null,
      title: 'Doctor within s. 44ADA',
      path: 'Gross receipts ₹42 lakh, below ₹50 lakh; profit above 50%.',
      input: base({ clientName: 'Dr. A. Sample, Physician (sample)', nature: 'profession', professionCategory: 'medical',
        turnover: '4200000', cashReceipts: '150000', profit: '2500000', totalIncome: '2560000' })
    },
    {
      id: 'case-06', expect: 'NOT APPLICABLE', ground: 'First proviso',
      title: 'Consultant at ₹60 lakh declaring under s. 44ADA',
      path: 'Receipts exceed ₹50 lakh, but cash is within 5% — ₹75 lakh ceiling. Income declared under s. 44ADA(1): s. 44AB does not apply (Finance Act 2023).',
      input: base({ clientName: 'R. Sample, Technical Consultant (sample)', nature: 'profession',
        professionCategory: 'technical-consultancy', turnover: '6000000', cashReceipts: '180000',
        profit: '3300000', totalIncome: '3300000', declarePresumptive: 'yes' })
    },
    {
      id: 'case-07', expect: 'APPLICABLE', ground: 's. 44AB(b)',
      title: 'Architects above ₹75 lakh',
      path: 'Gross receipts ₹82 lakh exceed even the enhanced s. 44ADA ceiling, so the presumptive route is closed. Audit under s. 44AB(b).',
      input: base({ clientName: 'Sample & Co., Architects (sample)', constitution: 'firm', nature: 'profession',
        professionCategory: 'architectural', turnover: '8200000', cashReceipts: '120000',
        profit: '4400000', totalIncome: '4400000' })
    },
    {
      id: 'case-08', expect: 'APPLICABLE', ground: 's. 44AB(d)',
      title: 'Professional declaring below 50% — first year',
      path: 'Receipts ₹38 lakh, profit 39%, income above the exemption. Section 44AB(d) has no prior-year condition — audit applies in the first year.',
      input: base({ clientName: 'Adv. P. Sample (sample)', nature: 'profession', professionCategory: 'legal',
        turnover: '3800000', cashReceipts: '50000', profit: '1500000', totalIncome: '1600000' })
    },
    {
      id: 'case-09', expect: 'APPLICABLE', ground: 's. 44AB(e)',
      title: 'Leaving s. 44AD after an earlier opt-in',
      path: 'Turnover ₹90 lakh, far below every limit. But s. 44AD was used earlier and profit is now 2.2% — s. 44AD(4) applies.',
      input: base({ clientName: 'Nandini Fabricators (sample)', turnover: '9000000',
        totalReceipts: '9000000', cashReceipts: '100000', totalPayments: '8600000', cashPayments: '90000',
        profit: '200000', totalIncome: '900000', bar44AD: 'no', prior44AD: 'yes' })
    },
    {
      id: 'case-10', expect: 'APPLICABLE', ground: 's. 44AB(e)',
      title: 'Firm within a s. 44AD(4) five-year bar',
      path: 'Turnover only ₹75 lakh, but the firm is barred under s. 44AD(4) and a firm has no basic exemption — audit applies whatever the turnover.',
      input: base({ clientName: 'Sample Brothers & Co. (sample)', constitution: 'firm', turnover: '7500000',
        totalReceipts: '7500000', cashReceipts: '210000', totalPayments: '7300000', cashPayments: '190000',
        profit: '180000', totalIncome: '180000', bar44AD: 'yes' })
    },
    {
      id: 'case-11', expect: 'APPLICABLE', ground: 's. 44AB(a)',
      title: 'Company above ₹10 crore',
      path: 'A company cannot use s. 44AD. Turnover ₹12 crore exceeds either limit. Audited under the Companies Act, so Form 3CA.',
      input: base({ clientName: 'Sample Industries Private Limited (sample)', constitution: 'company', turnover: '120000000',
        totalReceipts: '120000000', cashReceipts: '900000', totalPayments: '108000000', cashPayments: '800000',
        profit: '9400000', totalIncome: '9400000' })
    },
    {
      id: 'case-12', expect: 'NOT APPLICABLE', ground: null,
      title: 'Derivatives trader within limits',
      path: 'Turnover computed as per the ICAI Guidance Note is ₹30 lakh; profit exceeds 8% of it. Not applicable, with a note on the turnover computation.',
      input: base({ clientName: 'Sample Capital (proprietary) (sample)', turnover: '3000000',
        totalReceipts: '3000000', cashReceipts: '0', totalPayments: '2800000', cashPayments: '0',
        profit: '420000', totalIncome: '480000', bar44AD: 'no', flags: ['derivatives'] })
    }
  ];

  function byId(id) {
    for (var i = 0; i < cases.length; i++) if (cases[i].id === id) return cases[i];
    return null;
  }

  TAS.samples = { cases: cases, byId: byId };

})(window);
