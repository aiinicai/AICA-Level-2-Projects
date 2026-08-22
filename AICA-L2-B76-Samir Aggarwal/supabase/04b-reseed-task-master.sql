-- =====================================================================
--  Aggarwal Samir & Co — Task Delegation App
--  FILE 4b : Re-seed the task master from the firm's own list
--
--  Run 04a-add-weekly-recurrence.sql FIRST, on its own.
--
--  Generated from "New seeding.xlsx" — 68 tasks the firm kept.
--  Regular statutory compliance (GST returns, ITR, TDS returns, ROC annual
--  filings) is deliberately absent: that is tracked on the firm's separate
--  compliance platform. This catalogue is the event-driven and engagement
--  work that has no automatic trigger and therefore needs chasing.
--
--  Safe to re-run. Existing tasks already allocated are never touched.
-- =====================================================================

begin;

create temp table _wanted (
  name             text,
  category         text,
  recurrence       text,
  default_priority text
) on commit drop;

insert into _wanted (name, category, recurrence, default_priority) values

  -- ============ GST ============
  ('GST Registration - New'                      , 'GST'             , 'One-time'  , 'Medium'),
  ('GST Registration - Amendment'                , 'GST'             , 'One-time'  , 'Low'),
  ('GST Cancellation / Revocation'               , 'GST'             , 'One-time'  , 'Medium'),
  ('GST Notice / Departmental Reply'             , 'GST'             , 'One-time'  , 'Urgent'),
  ('GST Refund Application'                      , 'GST'             , 'One-time'  , 'Medium'),

  -- ============ INCOME TAX ============
  ('Transfer Pricing Report (Form 3CEB)'         , 'Income Tax'      , 'Annual'    , 'High'),
  ('Form 15CA / 15CB Certification'              , 'Income Tax'      , 'One-time'  , 'High'),
  ('Income Tax Notice / Scrutiny Reply'          , 'Income Tax'      , 'One-time'  , 'Urgent'),
  ('Rectification u/s 154'                       , 'Income Tax'      , 'One-time'  , 'Medium'),
  ('Appeal - CIT(A) Filing'                      , 'Income Tax'      , 'One-time'  , 'High'),
  ('Lower Deduction Certificate (Form 13)'       , 'Income Tax'      , 'One-time'  , 'Medium'),
  ('PAN / TAN Application'                       , 'Income Tax'      , 'One-time'  , 'Low'),

  -- ============ TDS/TCS ============
  ('TDS Default / Correction Statement'          , 'TDS/TCS'         , 'One-time'  , 'High'),

  -- ============ ROC/MCA ============
  ('ADT-1 (Auditor Appointment)'                 , 'ROC/MCA'         , 'One-time'  , 'Medium'),
  ('INC-20A (Commencement of Business)'          , 'ROC/MCA'         , 'One-time'  , 'High'),
  ('Company Incorporation (SPICe+)'              , 'ROC/MCA'         , 'One-time'  , 'High'),
  ('LLP Incorporation (FiLLiP)'                  , 'ROC/MCA'         , 'One-time'  , 'High'),
  ('Charge Creation / Satisfaction (CHG-1/4)'    , 'ROC/MCA'         , 'One-time'  , 'High'),
  ('Director Appointment / Resignation (DIR-12)' , 'ROC/MCA'         , 'One-time'  , 'Medium'),
  ('Board / AGM Minutes & Statutory Registers'   , 'ROC/MCA'         , 'Annual'    , 'Medium'),
  ('Board resolution'                            , 'ROC/MCA'         , 'One-time'  , 'Medium'),

  -- ============ AUDIT ============
  ('Statutory Audit'                             , 'Audit'           , 'Annual'    , 'Urgent'),
  ('Tax Audit Fieldwork'                         , 'Audit'           , 'Annual'    , 'Urgent'),
  ('Internal Audit'                              , 'Audit'           , 'Quarterly' , 'High'),
  ('Stock Audit'                                 , 'Audit'           , 'Quarterly' , 'Medium'),
  ('Physical Verification of Fixed Assets'       , 'Audit'           , 'Annual'    , 'Medium'),
  ('Client Visit'                                , 'Audit'           , 'One-time'  , 'Medium'),

  -- ============ INTERNAL OFFICE ============
  ('Documentation on Firm''s server'             , 'Internal Office' , 'One-time'  , 'Medium'),
  ('Promotional material / PPT'                  , 'Internal Office' , 'One-time'  , 'Medium'),

  -- ============ ECOMMERCE ============
  ('Promotional material / PPT'                  , 'Ecommerce'       , 'One-time'  , 'Medium'),
  ('Amazon/ Flipkart etc.'                       , 'Ecommerce'       , 'One-time'  , 'Medium'),

  -- ============ ACCOUNTING ============
  ('Weekly Bookkeeping / Data Entry'             , 'Accounting'      , 'Weekly'    , 'Medium'),
  ('Monthly Bookkeeping / Data Entry'            , 'Accounting'      , 'Monthly'   , 'Medium'),
  ('Bank Reconciliation Statement'               , 'Accounting'      , 'Monthly'   , 'Medium'),
  ('Ledger Scrutiny'                             , 'Accounting'      , 'Quarterly' , 'Medium'),
  ('Finalisation of Accounts'                    , 'Accounting'      , 'Annual'    , 'High'),
  ('Balance Sheet & P&L Preparation'             , 'Accounting'      , 'Annual'    , 'High'),
  ('Depreciation Schedule (Cos Act & IT Act)'    , 'Accounting'      , 'Annual'    , 'Medium'),
  ('Party / Vendor Ledger Reconciliation'        , 'Accounting'      , 'Quarterly' , 'Medium'),
  ('Tally Data Cleanup & Backup'                 , 'Accounting'      , 'Monthly'   , 'Low'),

  -- ============ PAYROLL ============
  ('Payroll Processing'                          , 'Payroll'         , 'Monthly'   , 'High'),
  ('Gratuity / Leave Encashment Computation'     , 'Payroll'         , 'Annual'    , 'Medium'),
  ('Labour Licence Renewal'                      , 'Payroll'         , 'Annual'    , 'Low'),

  -- ============ REGISTRATIONS ============
  ('Udyam / MSME Registration'                   , 'Registrations'   , 'One-time'  , 'Low'),
  ('Import Export Code (IEC)'                    , 'Registrations'   , 'One-time'  , 'Medium'),
  ('Trademark Application'                       , 'Registrations'   , 'One-time'  , 'Medium'),
  ('12A / 80G Registration'                      , 'Registrations'   , 'One-time'  , 'High'),
  ('FCRA Registration / Annual Return'           , 'Registrations'   , 'Annual'    , 'High'),
  ('Shop & Establishment Registration'           , 'Registrations'   , 'One-time'  , 'Low'),
  ('Net Worth Certificate'                       , 'Registrations'   , 'One-time'  , 'Medium'),
  ('Turnover Certificate'                        , 'Registrations'   , 'One-time'  , 'Medium'),
  ('Project Report / CMA Data Preparation'       , 'Registrations'   , 'One-time'  , 'High'),
  ('Bank Loan Documentation'                     , 'Registrations'   , 'One-time'  , 'Medium'),

  -- ============ FIRM INTERNAL ============
  ('Client Onboarding & KYC'                     , 'Firm Internal'   , 'One-time'  , 'Medium'),
  ('Engagement Letter Preparation'               , 'Firm Internal'   , 'One-time'  , 'Low'),
  ('Fee Billing & Invoicing'                     , 'Firm Internal'   , 'Monthly'   , 'Medium'),
  ('Fee Follow-up / Recovery'                    , 'Firm Internal'   , 'Monthly'   , 'Medium'),
  ('Document Collection from Client'             , 'Firm Internal'   , 'One-time'  , 'Medium'),
  ('Working Paper Filing / Archival'             , 'Firm Internal'   , 'One-time'  , 'Low'),
  ('Staff Training Session'                      , 'Firm Internal'   , 'One-time'  , 'Low'),

  -- ============ ADVISORY ============
  ('Financial Due Diligence'                     , 'Advisory'        , 'One-time'  , 'High'),
  ('Business Valuation'                          , 'Advisory'        , 'One-time'  , 'High'),

  -- ============ ACCOUNTING ============
  ('Management Reporting Pack (MIS)'             , 'Accounting'      , 'Monthly'   , 'Medium'),
  ('Cash Flow Projection'                        , 'Accounting'      , 'One-time'  , 'Medium'),
  ('Fixed Asset Register Creation'               , 'Accounting'      , 'One-time'  , 'Medium'),
  ('Stock & Debtor Statement to Bank'            , 'Accounting'      , 'Monthly'   , 'Medium'),
  ('Data Migration / Software Setup for Client'  , 'Accounting'      , 'One-time'  , 'Medium'),

  -- ============ ADVISORY ============
  ('SOP / Process Documentation'                 , 'Advisory'        , 'One-time'  , 'Medium');

-- 1. Add the new ones, and refresh + reactivate any that already existed.
insert into public.task_master (name, category, recurrence, default_priority, is_active)
select w.name,
       w.category,
       w.recurrence::public.recurrence,
       w.default_priority::public.task_priority,
       true
from _wanted w
on conflict (name, category) do update
  set recurrence       = excluded.recurrence,
      default_priority = excluded.default_priority,
      is_active        = true;

-- 2. Remove anything the firm dropped — but only where nothing depends on it.
delete from public.task_master tm
where not exists (
        select 1 from _wanted w
        where w.name = tm.name and w.category = tm.category)
  and not exists (select 1 from public.tasks t where t.task_master_id = tm.id)
  and not exists (
        select 1 from public.recurring_assignments ra where ra.task_master_id = tm.id);

-- 3. Anything dropped but still referenced by a real task is deactivated
--    instead, so history survives while it stops appearing on allocation.
update public.task_master tm
set is_active = false
where not exists (
        select 1 from _wanted w
        where w.name = tm.name and w.category = tm.category);

commit;

-- =====================================================================
--  Verify:
--    select category, count(*) filter (where is_active) as active,
--           count(*) as total
--    from public.task_master group by 1 order by 1;
--
--  Expect 68 active rows across 12 categories,
--  and 0 inactive on a system with no allocated tasks yet.
-- =====================================================================
