-- =====================================================================
--  Aggarwal Samir & Co — Task Delegation App
--  FILE 2 of 2 : Predefined task master for an Indian CA firm
--  Run AFTER 01-schema.sql. Idempotent (ON CONFLICT DO NOTHING).
--  Admin can add / deactivate more rows from the app UI afterwards.
-- =====================================================================

insert into public.task_master (name, category, recurrence, default_priority, statutory_due, estimated_hours) values

-- ============ GST ============
('GSTR-1 (Monthly)',                          'GST', 'Monthly',   'High',   '11th of following month',         2.0),
('GSTR-1 / IFF (QRMP)',                       'GST', 'Quarterly', 'High',   '13th of month following quarter', 2.0),
('GSTR-3B',                                   'GST', 'Monthly',   'Urgent', '20th of following month',         2.5),
('GSTR-9 Annual Return',                      'GST', 'Annual',    'High',   '31st December',                   8.0),
('GSTR-9C Reconciliation Statement',          'GST', 'Annual',    'High',   '31st December',                  10.0),
('GST Input Reconciliation (2A/2B vs Books)', 'GST', 'Monthly',   'High',   null,                              3.0),
('GST Registration - New',                    'GST', 'One-time',  'Medium', null,                              3.0),
('GST Registration - Amendment',              'GST', 'One-time',  'Low',    null,                              1.5),
('GST Cancellation / Revocation',             'GST', 'One-time',  'Medium', null,                              2.0),
('LUT Filing (Exporters)',                    'GST', 'Annual',    'Medium', '31st March',                      1.0),
('E-Way Bill Compliance Review',              'GST', 'Monthly',   'Low',    null,                              1.0),
('GST Notice / Departmental Reply',           'GST', 'One-time',  'Urgent', null,                              6.0),
('GST Refund Application',                    'GST', 'One-time',  'Medium', null,                              5.0),

-- ============ INCOME TAX ============
('ITR - Individual / HUF',                    'Income Tax', 'Annual',   'High',   '31st July / 31st Oct', 3.0),
('ITR - Partnership Firm / LLP',              'Income Tax', 'Annual',   'High',   '31st July / 31st Oct', 4.0),
('ITR - Company',                             'Income Tax', 'Annual',   'High',   '31st October',         6.0),
('ITR - Trust / Society',                     'Income Tax', 'Annual',   'High',   '31st October',         5.0),
('Advance Tax Computation',                   'Income Tax', 'Quarterly','Urgent', '15 Jun/Sep/Dec/Mar',   2.0),
('Tax Audit u/s 44AB (Form 3CA/3CB + 3CD)',   'Income Tax', 'Annual',   'Urgent', '30th September',      12.0),
('Transfer Pricing Report (Form 3CEB)',       'Income Tax', 'Annual',   'High',   '31st October',        10.0),
('Form 15CA / 15CB Certification',            'Income Tax', 'One-time', 'High',   null,                   1.5),
('Income Tax Notice / Scrutiny Reply',        'Income Tax', 'One-time', 'Urgent', null,                   8.0),
('Rectification u/s 154',                     'Income Tax', 'One-time', 'Medium', null,                   2.0),
('Appeal - CIT(A) Filing',                    'Income Tax', 'One-time', 'High',   null,                  10.0),
('Lower Deduction Certificate (Form 13)',     'Income Tax', 'One-time', 'Medium', null,                   4.0),
('PAN / TAN Application',                     'Income Tax', 'One-time', 'Low',    null,                   1.0),

-- ============ TDS / TCS ============
('TDS Return 24Q (Salary)',                   'TDS/TCS', 'Quarterly', 'High',   '31 Jul/Oct/Jan/May', 3.0),
('TDS Return 26Q (Non-Salary)',               'TDS/TCS', 'Quarterly', 'High',   '31 Jul/Oct/Jan/May', 3.0),
('TDS Return 27Q (Non-Resident)',             'TDS/TCS', 'Quarterly', 'High',   '31 Jul/Oct/Jan/May', 3.0),
('TCS Return 27EQ',                           'TDS/TCS', 'Quarterly', 'High',   '15 Jul/Oct/Jan/May', 2.5),
('Monthly TDS Payment / Challan',             'TDS/TCS', 'Monthly',   'Urgent', '7th of following month', 1.0),
('Form 16 Issuance',                          'TDS/TCS', 'Annual',    'High',   '15th June',          3.0),
('Form 16A Issuance',                         'TDS/TCS', 'Quarterly', 'Medium', '15 days from due date', 1.5),
('TDS Reconciliation (26AS / AIS / TIS)',     'TDS/TCS', 'Quarterly', 'High',   null,                 2.5),
('TDS Default / Correction Statement',        'TDS/TCS', 'One-time',  'High',   null,                 3.0),

-- ============ ROC / MCA ============
('AOC-4 (Financial Statements)',              'ROC/MCA', 'Annual',      'High',   '30 days from AGM', 3.0),
('MGT-7 / MGT-7A (Annual Return)',            'ROC/MCA', 'Annual',      'High',   '60 days from AGM', 3.0),
('DIR-3 KYC',                                 'ROC/MCA', 'Annual',      'Medium', '30th September',   0.5),
('ADT-1 (Auditor Appointment)',               'ROC/MCA', 'One-time',    'Medium', '15 days from AGM', 1.0),
('INC-20A (Commencement of Business)',        'ROC/MCA', 'One-time',    'High',   '180 days from incorporation', 1.0),
('DPT-3 (Return of Deposits)',                'ROC/MCA', 'Annual',      'Medium', '30th June',        2.0),
('MSME-1 (Half-Yearly Return)',               'ROC/MCA', 'Half-Yearly', 'Medium', '30 Apr / 31 Oct',  1.5),
('LLP Form 8 (Statement of Account)',         'ROC/MCA', 'Annual',      'High',   '30th October',     2.0),
('LLP Form 11 (Annual Return)',               'ROC/MCA', 'Annual',      'High',   '30th May',         1.5),
('Company Incorporation (SPICe+)',            'ROC/MCA', 'One-time',    'High',   null,               8.0),
('LLP Incorporation (FiLLiP)',                'ROC/MCA', 'One-time',    'High',   null,               6.0),
('Charge Creation / Satisfaction (CHG-1/4)',  'ROC/MCA', 'One-time',    'High',   '30 days from creation', 2.0),
('Director Appointment / Resignation (DIR-12)','ROC/MCA','One-time',    'Medium', '30 days',          1.5),
('Board / AGM Minutes & Statutory Registers', 'ROC/MCA', 'Annual',      'Medium', null,               4.0),

-- ============ AUDIT & ASSURANCE ============
('Statutory Audit',                           'Audit', 'Annual',   'Urgent', null, 40.0),
('Tax Audit Fieldwork',                       'Audit', 'Annual',   'Urgent', null, 20.0),
('Internal Audit',                            'Audit', 'Quarterly','High',   null, 25.0),
('Bank Audit - Statutory Branch',             'Audit', 'Annual',   'Urgent', null, 30.0),
('Bank Audit - Concurrent',                   'Audit', 'Monthly',  'High',   null, 15.0),
('Stock Audit',                               'Audit', 'Quarterly','Medium', null, 10.0),
('Trust / NGO Audit',                         'Audit', 'Annual',   'High',   null, 15.0),
('Co-operative Society Audit',                'Audit', 'Annual',   'Medium', null, 15.0),
('Physical Verification of Fixed Assets',     'Audit', 'Annual',   'Medium', null,  8.0),

-- ============ ACCOUNTING & BOOKKEEPING ============
('Monthly Bookkeeping / Data Entry',          'Accounting', 'Monthly', 'Medium', null, 8.0),
('Bank Reconciliation Statement',             'Accounting', 'Monthly', 'Medium', null, 2.0),
('Ledger Scrutiny',                           'Accounting', 'Quarterly','Medium',null, 4.0),
('Finalisation of Accounts',                  'Accounting', 'Annual',  'High',   null, 12.0),
('Balance Sheet & P&L Preparation',           'Accounting', 'Annual',  'High',   null, 8.0),
('Depreciation Schedule (Cos Act & IT Act)',  'Accounting', 'Annual',  'Medium', null, 3.0),
('Party / Vendor Ledger Reconciliation',      'Accounting', 'Quarterly','Medium',null, 3.0),
('Tally Data Cleanup & Backup',               'Accounting', 'Monthly', 'Low',    null, 2.0),

-- ============ PAYROLL & LABOUR ============
('Payroll Processing',                        'Payroll', 'Monthly', 'High',   'Month end',              3.0),
('PF Return Filing (ECR)',                    'Payroll', 'Monthly', 'Urgent', '15th of following month',1.5),
('ESI Return Filing',                         'Payroll', 'Monthly', 'Urgent', '15th of following month',1.5),
('Professional Tax Return',                   'Payroll', 'Monthly', 'Medium', 'State specific',         1.0),
('Gratuity / Leave Encashment Computation',   'Payroll', 'Annual',  'Medium', null,                     2.0),
('Labour Licence Renewal',                    'Payroll', 'Annual',  'Low',    null,                     2.0),

-- ============ REGISTRATIONS & CERTIFICATIONS ============
('Udyam / MSME Registration',                 'Registrations', 'One-time', 'Low',    null, 1.0),
('Import Export Code (IEC)',                  'Registrations', 'One-time', 'Medium', null, 2.0),
('Trademark Application',                     'Registrations', 'One-time', 'Medium', null, 3.0),
('12A / 80G Registration',                    'Registrations', 'One-time', 'High',   null, 6.0),
('FCRA Registration / Annual Return',         'Registrations', 'Annual',   'High',   '31st December', 5.0),
('Shop & Establishment Registration',         'Registrations', 'One-time', 'Low',    null, 1.5),
('Net Worth Certificate',                     'Registrations', 'One-time', 'Medium', null, 2.0),
('Turnover Certificate',                      'Registrations', 'One-time', 'Medium', null, 1.5),
('Project Report / CMA Data Preparation',     'Registrations', 'One-time', 'High',   null, 10.0),
('Bank Loan Documentation',                   'Registrations', 'One-time', 'Medium', null, 6.0),

-- ============ FIRM INTERNAL ============
('Client Onboarding & KYC',                   'Firm Internal', 'One-time', 'Medium', null, 2.0),
('Engagement Letter Preparation',             'Firm Internal', 'One-time', 'Low',    null, 1.0),
('Fee Billing & Invoicing',                   'Firm Internal', 'Monthly',  'Medium', null, 2.0),
('Fee Follow-up / Recovery',                  'Firm Internal', 'Monthly',  'Medium', null, 2.0),
('Document Collection from Client',           'Firm Internal', 'One-time', 'Medium', null, 1.0),
('Working Paper Filing / Archival',           'Firm Internal', 'One-time', 'Low',    null, 2.0),
('Staff Training Session',                    'Firm Internal', 'One-time', 'Low',    null, 3.0),
('Internal Review by Partner',                'Firm Internal', 'One-time', 'High',   null, 2.0)

on conflict (name, category) do nothing;

-- =====================================================================
--  Sanity check — run these after the two files:
--    select category, count(*) from public.task_master group by 1 order by 1;
--    -- expect ~89 rows across 9 categories
-- =====================================================================
