"""A form on the first page a user ever loads must be submittable."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestTheFirstPageCarriesAToken:
    """Decision 70.

    The CSRF cookie was set on the RESPONSE, after the template had already
    rendered. Templates read `request.cookies`, so on a fresh installation the
    first page a user opened carried an empty token in every form and their
    first submission failed with "Field required". Refreshing hid it, which is
    why it reached a packaged build.
    """

    def test_a_brand_new_visitor_gets_a_usable_token(self, app_client: TestClient) -> None:
        app_client.cookies.clear()
        body = app_client.get("/clients/new").text
        import re

        tokens = re.findall(r'name="csrf_token" value="([^"]*)"', body)
        assert tokens, "the page has no csrf field at all"
        assert all(t for t in tokens), "the first page rendered an empty token"

    def test_the_token_matches_the_cookie_it_will_be_checked_against(
        self, app_client: TestClient
    ) -> None:
        app_client.cookies.clear()
        response = app_client.get("/clients/new")
        import re

        rendered = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
        assert rendered is not None
        assert rendered.group(1) == response.cookies.get("auditcraft_csrf")

    def test_an_existing_visitor_keeps_the_token_they_have(self, app_client: TestClient) -> None:
        """Reissuing on every request would break a form open in another tab."""
        app_client.cookies.clear()
        first = app_client.get("/clients/new")
        issued = first.cookies.get("auditcraft_csrf")
        assert issued

        import re

        second = app_client.get("/clients/new")
        rendered = re.search(r'name="csrf_token" value="([^"]+)"', second.text)
        assert rendered is not None
        assert rendered.group(1) == issued
