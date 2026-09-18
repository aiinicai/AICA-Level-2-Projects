CREATE OR REPLACE FUNCTION public.create_app_user(
  _name text, _phone text, _email text, _password text, _role text, _status text
)
RETURNS TABLE (id uuid, name text, phone text, email text, role text, status text, created_at timestamptz)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
BEGIN
  RETURN QUERY
  INSERT INTO public.app_users (name, phone, email, password_hash, role, status)
  VALUES (_name, _phone, _email, extensions.crypt(_password, extensions.gen_salt('bf')), _role, _status)
  RETURNING app_users.id, app_users.name, app_users.phone, app_users.email,
            app_users.role, app_users.status, app_users.created_at;
END;
$$;

CREATE OR REPLACE FUNCTION public.verify_app_user(_identifier text, _password text)
RETURNS TABLE (id uuid, name text, phone text, email text, role text, status text, created_at timestamptz)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
BEGIN
  RETURN QUERY
  SELECT u.id, u.name, u.phone, u.email, u.role, u.status, u.created_at
  FROM public.app_users u
  WHERE (u.phone = _identifier OR lower(u.email) = lower(_identifier))
    AND u.password_hash = extensions.crypt(_password, u.password_hash)
  LIMIT 1;
END;
$$;

CREATE OR REPLACE FUNCTION public.set_app_user_password(_user_id uuid, _password text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
BEGIN
  UPDATE public.app_users
  SET password_hash = extensions.crypt(_password, extensions.gen_salt('bf'))
  WHERE id = _user_id;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.create_app_user(text, text, text, text, text, text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.verify_app_user(text, text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.set_app_user_password(uuid, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_app_user(text, text, text, text, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.verify_app_user(text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.set_app_user_password(uuid, text) TO service_role;