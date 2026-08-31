"""No screen may print a raw amount or an ISO date. §12, §19.

`group_indian` lived in the document renderer and nowhere else, so the
annexure printed "42,60,000" while the What Changed screen printed
"4260000.00" for the same figure. That was found by opening the page, not by
a test — every unit test exercised the layer below the template.

So this sweeps the actual HTML of every page instead of trusting that each
new screen remembered to call the formatter. It is deliberately a property
over all output rather than a check of particular fields: the failure mode is
a surface nobody thought about.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engagement import Engagement
from tests.test_client_routes import _sign_in

# "4260000.00" — four or more digits with a decimal tail. Money that has not
# been through `group_indian`. Grouped output contains commas, so it cannot
# match; a year or a small integer has no decimal tail.
RAW_AMOUNT = re.compile(r"(?<![\d,.])\d{4,}\.\d{2}(?![\d])")

# "2026-03-31" outside an attribute. Date inputs legitimately carry ISO values
# in `value="..."`, which is what the HTML date control requires, so those are
# excluded rather than the pattern being weakened.
ISO_DATE = re.compile(r"(?<![\w=\"'/-])\d{4}-\d{2}-\d{2}(?![\w\"'-])")


def _pages(engagement_id: int) -> list[str]:
    return [
        "/",
        "/clients",
        "/clients/1",
        "/admin/firm",
        "/admin/needs-review",
        "/admin/audit-log",
        f"/engagements/{engagement_id}",
        f"/engagements/{engagement_id}/validation",
        f"/engagements/{engagement_id}/roll-forward",
        f"/engagements/{engagement_id}/applicability",
    ]


@pytest.fixture
def engagement_id(db: Session) -> int:
    found = db.scalar(select(Engagement).where(Engagement.fy_code == "2025-26"))
    assert found is not None
    return found.engagement_id


def _strip_inputs(html: str) -> str:
    """Remove form control values, which hold raw values by design."""
    return re.sub(r"<input\b[^>]*>", "", html)


class TestNoRawNumbersOnAnyScreen:
    def test_no_ungrouped_amount(self, app_client: TestClient, engagement_id: int) -> None:
        _sign_in(app_client)
        offenders: list[str] = []
        for path in _pages(engagement_id):
            response = app_client.get(path)
            if response.status_code != 200:
                continue
            for match in RAW_AMOUNT.finditer(_strip_inputs(response.text)):
                offenders.append(f"{path}: {match.group(0)}")
        assert not offenders, "amounts printed without Indian grouping:\n  " + "\n  ".join(
            sorted(set(offenders))
        )

    def test_no_iso_date_in_body_text(self, app_client: TestClient, engagement_id: int) -> None:
        _sign_in(app_client)
        offenders: list[str] = []
        for path in _pages(engagement_id):
            response = app_client.get(path)
            if response.status_code != 200:
                continue
            for match in ISO_DATE.finditer(_strip_inputs(response.text)):
                offenders.append(f"{path}: {match.group(0)}")
        assert not offenders, "ISO dates shown to the user:\n  " + "\n  ".join(
            sorted(set(offenders))
        )

    def test_every_page_under_test_actually_loads(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        """A 500 would make both checks above pass by having nothing to scan."""
        _sign_in(app_client)
        broken = [
            f"{path} -> {app_client.get(path).status_code}"
            for path in _pages(engagement_id)
            if app_client.get(path).status_code >= 400
        ]
        assert not broken, "pages not loading:\n  " + "\n  ".join(broken)


class TestEveryNavigationLinkResolves:
    """No link in the sidebar may 404.

    The Documents group linked to `/documents/{document_id}/preview`, one path
    segment short of the route, so every one of the six previews 404'd and the
    generated documents could only be reached by typing a URL. Nothing caught
    it: the preview route had its own tests and they called the correct URL
    directly.
    """

    def test_no_sidebar_link_is_dead(self, app_client: TestClient, engagement_id: int) -> None:
        _sign_in(app_client)
        hrefs: set[str] = set()
        for path in _pages(engagement_id):
            response = app_client.get(path)
            if response.status_code != 200:
                continue
            hrefs.update(re.findall(r'<a[^>]+href="(/[^"#?]*)"', response.text))

        assert hrefs, "no links found — the sidebar is missing"
        broken = [
            f"{href} -> {code}"
            for href in sorted(hrefs)
            if (code := app_client.get(href).status_code) >= 400
        ]
        assert not broken, "dead links in the interface:\n  " + "\n  ".join(broken)

    def test_a_document_preview_is_linked_from_the_workspace(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        """The specific thing the user could not do: reach a preview by clicking."""
        _sign_in(app_client)
        body = app_client.get(f"/engagements/{engagement_id}").text
        links = re.findall(r'href="(/documents/[^"]+/preview)"', body)
        assert links, "the workspace offers no way to open a generated document"
        for href in links:
            assert app_client.get(href).status_code == 200, href


class TestNothingIsReachableOnlyByTyping:
    """Every screen must be reachable by clicking.

    The engagement workspace — where every clause is answered — could not be
    opened from anywhere. The dashboard and the client screen both listed
    engagements as plain text, and every link to `/engagements/{id}` lived on a
    page you could only reach from inside an engagement already. The user found
    it by looking for the clause dropdowns and not finding them.

    `TestEveryNavigationLinkResolves` could never have caught this: a *missing*
    link is not a broken one. This asserts the other half.
    """

    def test_the_workspace_is_linked_from_the_dashboard(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        _sign_in(app_client)
        body = app_client.get("/").text
        assert (
            f'href="/engagements/{engagement_id}"' in body
        ), "the dashboard lists engagements but does not link to them"

    def test_the_workspace_is_linked_from_the_client_screen(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        _sign_in(app_client)
        body = app_client.get("/clients/1?tab=financial-years").text
        assert (
            f'href="/engagements/{engagement_id}"' in body
        ), "the client's financial years do not open the workspace"

    def test_the_workspace_offers_the_clause_controls(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        """What the user was looking for: the clause dropdowns and the
        document previews, on the page the links now reach."""
        _sign_in(app_client)
        body = app_client.get(f"/engagements/{engagement_id}").text
        assert "<select" in body, "no clause dropdowns on the workspace"
        assert 'class="autosave"' in body
        assert "/preview" in body, "no way to open a generated document"

    def test_no_screen_still_promises_a_finished_phase(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        """Two empty states still read "arrives in Phase 6" long after it
        shipped, which tells a user the feature does not exist yet."""
        _sign_in(app_client)
        for path in _pages(engagement_id):
            response = app_client.get(path)
            if response.status_code != 200:
                continue
            assert "Phase 6" not in response.text, f"{path} still refers to an unfinished phase"
