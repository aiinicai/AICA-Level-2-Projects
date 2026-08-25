-- =====================================================================
--  FILE 4a : Add "Weekly" to the recurrence enum
--
--  RUN THIS ON ITS OWN, BEFORE 04b-reseed-task-master.sql.
--
--  Postgres will not let a newly added enum value be USED in the same
--  transaction that added it. Keeping this in its own run is the whole
--  reason it is a separate file — pasting it above the reseed produces
--  "unsafe use of new value of enum type".
-- =====================================================================

alter type public.recurrence add value if not exists 'Weekly' before 'Monthly';

-- Verify (should list: One-time, Weekly, Monthly, Quarterly, Half-Yearly, Annual):
--   select unnest(enum_range(null::public.recurrence));
