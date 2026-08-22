-- =====================================================================
--  FILE 8a : Add "Daily" to the recurrence enum
--
--  RUN THIS ON ITS OWN, BEFORE 08b-daily-autogeneration.sql.
--  Same reason as 04a: Postgres refuses to USE a new enum value in the
--  transaction that added it.
-- =====================================================================

alter type public.recurrence add value if not exists 'Daily' before 'Weekly';

-- Verify (should list: One-time, Daily, Weekly, Monthly, Quarterly, Half-Yearly, Annual):
--   select unnest(enum_range(null::public.recurrence));
