class TenantMiddleware:
    """Attaches the caller's tenant to every request as `request.firm` (None when signed out).
    The tenant comes from the authenticated user's record, never from the URL or POST data."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        request.firm = user.firm if user.is_authenticated else None
        return self.get_response(request)
