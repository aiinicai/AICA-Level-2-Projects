
REVOKE ALL ON FUNCTION public.has_role(uuid, public.app_role) FROM anon, public;
GRANT EXECUTE ON FUNCTION public.has_role(uuid, public.app_role) TO authenticated;

REVOKE ALL ON FUNCTION public.next_document_number(text) FROM anon, public;
GRANT EXECUTE ON FUNCTION public.next_document_number(text) TO authenticated;

REVOKE ALL ON FUNCTION public.handle_new_user() FROM anon, authenticated, public;
REVOKE ALL ON FUNCTION public.validate_grn_line() FROM anon, public;
