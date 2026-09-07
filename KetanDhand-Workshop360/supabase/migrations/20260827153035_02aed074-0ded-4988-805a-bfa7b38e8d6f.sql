-- These tables back a custom phone/password auth system and hold password
-- hashes, session tokens and customer PII. They are only ever reached from
-- trusted server functions using the service role, never from the browser.
-- Lock them down explicitly instead of relying on the absence of grants.

REVOKE ALL ON public.app_users FROM anon, authenticated;
REVOKE ALL ON public.app_sessions FROM anon, authenticated;
REVOKE ALL ON public.repairs FROM anon, authenticated;

GRANT ALL ON public.app_users TO service_role;
GRANT ALL ON public.app_sessions TO service_role;
GRANT ALL ON public.repairs TO service_role;

ALTER TABLE public.app_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.repairs ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.app_users FORCE ROW LEVEL SECURITY;
ALTER TABLE public.app_sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE public.repairs FORCE ROW LEVEL SECURITY;

-- Explicit deny-all policies: restrictive policies that never pass, so any
-- direct Data API access is refused even if a grant is added by mistake.
DROP POLICY IF EXISTS "No direct client access to app_users" ON public.app_users;
CREATE POLICY "No direct client access to app_users"
  ON public.app_users
  AS RESTRICTIVE
  FOR ALL
  TO anon, authenticated
  USING (false)
  WITH CHECK (false);

DROP POLICY IF EXISTS "No direct client access to app_sessions" ON public.app_sessions;
CREATE POLICY "No direct client access to app_sessions"
  ON public.app_sessions
  AS RESTRICTIVE
  FOR ALL
  TO anon, authenticated
  USING (false)
  WITH CHECK (false);

DROP POLICY IF EXISTS "No direct client access to repairs" ON public.repairs;
CREATE POLICY "No direct client access to repairs"
  ON public.repairs
  AS RESTRICTIVE
  FOR ALL
  TO anon, authenticated
  USING (false)
  WITH CHECK (false);

COMMENT ON TABLE public.app_users IS 'Workshop staff accounts incl. bcrypt password hashes. Server-only: accessed exclusively by trusted server functions via the service role. No client access.';
COMMENT ON TABLE public.app_sessions IS 'Opaque login session tokens. Server-only: accessed exclusively by trusted server functions via the service role. No client access.';
COMMENT ON TABLE public.repairs IS 'Repair jobs incl. customer PII. Server-only: accessed exclusively by trusted server functions via the service role after session + role checks. No client access.';