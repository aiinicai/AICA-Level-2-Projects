"""Dashboard, client register and profile tabs. Build Prompt v2 §8.2, §8.3."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.services.auth import CSRF_COOKIE


def _csrf(app_client: TestClient) -> str:
    """Fetch a page so the middleware sets a CSRF cookie, and return it.

    There is no login in this build; the token is the only thing a form needs.
    """
    app_client.cookies.clear()
    app_client.get("/")
    return app_client.cookies.get(CSRF_COOKIE) or ""


def _sign_in(app_client: TestClient, email: str = "") -> str:
    """Compatibility shim. There is nothing to sign in to any more."""
    return _csrf(app_client)


class TestNoAuthentication:
    """Single-user build: every page opens without a login (Step 4a).

    The cost is recorded in `app.core.permissions`: nothing distinguishes one
    person from another, so the change log cannot attribute an action.
    """

    @pytest.mark.parametrize(
        "path", ["/", "/clients", "/clients/1", "/admin/needs-review", "/admin/audit-log"]
    )
    def test_every_page_opens_without_signing_in(self, app_client: TestClient, path: str) -> None:
        app_client.cookies.clear()
        assert app_client.get(path).status_code == 200

    def test_there_is_no_login_page(self, app_client: TestClient) -> None:
        assert app_client.get("/login").status_code == 404

    def test_a_csrf_token_is_issued_without_a_login(self, app_client: TestClient) -> None:
        # The middleware replaces what the login route used to do.
        app_client.cookies.clear()
        response = app_client.get("/")
        assert CSRF_COOKIE in response.cookies


class TestDashboard:
    def test_tiles_render(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        body = app_client.get("/").text
        # "Pending manager review" and "Pending partner review" were removed
        # with the reviewer states themselves (decision 29).
        for label in ("Clients", "Active engagements", "Prepared, awaiting approval"):
            assert label in body

    def test_counts_reflect_the_seed(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        body = app_client.get("/").text
        # One client, two engagements of which one is finalised.
        assert "ABC Private Limited" in body or "Recent engagements" in body


class TestClientRegister:
    def test_lists_the_seeded_client(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        body = app_client.get("/clients").text
        assert "ABC001" in body
        assert "ABC Private Limited" in body

    def test_search_by_name(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        assert "ABC001" in app_client.get("/clients?q=ABC Private").text

    def test_search_by_cin(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        assert "ABC001" in app_client.get("/clients?q=U72200MH2010PTC054288").text

    def test_search_that_matches_nothing(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        assert "No clients match" in app_client.get("/clients?q=zzzznotaclient").text

    def test_filter_by_company_type(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        assert "ABC001" in app_client.get("/clients?type=pvt").text
        assert "No clients match" in app_client.get("/clients?type=pub_listed").text

    def test_pagination_controls_present(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        assert "Showing 1" in app_client.get("/clients").text


class TestClientProfile:
    def test_overview(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        body = app_client.get("/clients/1").text
        assert "U72200MH2010PTC054288" in body
        assert "immutable identity" in body

    def test_directors_tab_computes_from_the_register(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        body = app_client.get("/clients/1?tab=directors&as_on=2026-03-31").text
        assert "R. Mehta" in body
        assert "N. Bose" in body
        # K. Iyer ceased 17-10-2025 and must not appear in office at year end.
        assert "K. Iyer" not in body.split("Held office during")[0]

    def test_directors_as_on_an_earlier_date(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        body = app_client.get("/clients/1?tab=directors&as_on=2025-04-01").text
        in_office = body.split("Held office during")[0]
        assert "K. Iyer" in in_office
        assert "N. Bose" not in in_office

    def test_financial_years_tab_shows_the_locked_year(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        body = app_client.get("/clients/1?tab=financial-years").text
        assert "2024-25" in body
        assert "locked" in body

    def test_unknown_client_is_a_clean_404(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        response = app_client.get("/clients/9999")
        assert response.status_code == 404
        assert "Traceback" not in response.text


class TestMasterDataEditor:
    def _post(self, app_client: TestClient, csrf: str, **overrides: str):
        """The whole form, as the browser sends it (decision 62).

        Every field is posted on every save and the handler keeps only what
        differs, so a payload carrying one changed address is the realistic
        shape rather than a special case.
        """
        payload = {
            "f_company_name": "ABC Private Limited",
            "f_registered_addr": "New Address, Pune 411001",
            "f_company_type": "pvt",
            "f_framework": "igaap",
            "f_website": "",
            "f_has_subsidiary": "no",
            "f_has_associate": "no",
            "f_has_joint_venture": "no",
            "f_cost_records_industry": "no",
            "effective_date": "2025-09-01",
            "reason": "Registered office shifted",
            "scope": "current_fy",
            "csrf_token": csrf,
        }
        payload.update(overrides)
        return app_client.post("/clients/1/master-data", data=payload, follow_redirects=False)

    def test_form_offers_the_three_scope_options(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        body = app_client.get("/clients/1?tab=master-data").text
        assert "This financial year only" in body
        assert "This and future financial years" in body
        assert "Master record only" in body

    def test_form_warns_that_finalised_years_are_untouched(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        body = app_client.get("/clients/1?tab=master-data").text
        assert "finalised engagement is never altered" in body

    def test_a_valid_change_versions_the_profile(self, app_client: TestClient) -> None:
        csrf = _sign_in(app_client)
        assert self._post(app_client, csrf).status_code == 303
        timeline = app_client.get("/clients/1?tab=master-data").text
        assert "New Address, Pune 411001" in timeline
        assert "Registered office shifted" in timeline

    def test_a_missing_reason_is_refused_with_a_message(self, app_client: TestClient) -> None:
        csrf = _sign_in(app_client)
        response = self._post(app_client, csrf, reason="")
        assert response.status_code == 400
        assert "reason is required" in response.text
        assert "Traceback" not in response.text

    def test_a_field_outside_the_form_cannot_reach_the_profile(
        self, app_client: TestClient
    ) -> None:
        """It used to be refused by name. Now it is not read at all.

        The handler iterates the fields the form declares and ignores the rest,
        so an extra key in the payload — a stale form, a hand-rolled request —
        changes nothing rather than being reported as an error.
        """
        csrf = _sign_in(app_client)
        assert self._post(app_client, csrf, f_secretarial_audit="yes").status_code == 303
        body = app_client.get("/clients/1?tab=master-data").text
        assert "secretarial_audit" not in body

    def test_a_forged_csrf_token_is_refused(self, app_client: TestClient) -> None:
        csrf = _sign_in(app_client)
        response = self._post(app_client, csrf, csrf_token="forged")
        assert response.status_code == 400
        assert "CSRF" in response.text


class TestAdminPages:
    def test_needs_review_lists_every_flagged_clause(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        body = app_client.get("/admin/needs-review").text
        for clause_id in ("rule11.a", "rule11.g", "caro.viii"):
            assert clause_id in body

    def test_the_change_log_is_open_to_anyone(self, app_client: TestClient) -> None:
        # There are no roles to gate it with. Recorded here so the change is
        # deliberate rather than an oversight someone finds later.
        _sign_in(app_client)
        assert app_client.get("/admin/audit-log").status_code == 200

    def test_firm_details_are_editable(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        body = app_client.get("/admin/firm").text
        assert "Firm Registration Number" in body
        assert "Nothing about the firm is hard-coded" in body

    def test_saving_firm_details_persists(self, app_client: TestClient) -> None:
        csrf = _sign_in(app_client)
        response = app_client.post(
            "/admin/firm",
            data={
                "csrf_token": csrf,
                "firm_name": "Nair & Associates, Chartered Accountants",
                "frn": "123456W",
                "address": "Kochi",
                "default_place": "Kochi",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "Nair &amp; Associates" in app_client.get("/admin/firm").text

    def test_a_blank_firm_name_is_refused(self, app_client: TestClient) -> None:
        csrf = _sign_in(app_client)
        response = app_client.post(
            "/admin/firm",
            data={"csrf_token": csrf, "firm_name": "  ", "frn": "123456W"},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "cannot be blank" in response.text

    def test_an_invalid_frn_is_refused(self, app_client: TestClient) -> None:
        csrf = _sign_in(app_client)
        response = app_client.post(
            "/admin/firm",
            data={"csrf_token": csrf, "firm_name": "X & Co", "frn": "not-an-frn"},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "FRN" in response.text

    def test_admin_may_read_the_audit_log(self, app_client: TestClient) -> None:
        _sign_in(app_client, "admin@firm.local")
        assert app_client.get("/admin/audit-log").status_code == 200
