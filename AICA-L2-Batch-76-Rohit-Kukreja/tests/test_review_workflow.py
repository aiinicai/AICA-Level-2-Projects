"""The §17 definition-of-done journey, over HTTP.

*"The project is not complete because the forms work."* This walks the
journey §17 describes, as far as the sample clause repository allows.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engagement import Engagement
from app.models.enums import EngagementStatus
from tests.test_client_routes import _sign_in

UDIN = "26123456AB1234CD56"


@pytest.fixture
def engagement_id(db: Session, client_id: int) -> int:
    found = db.scalar(
        select(Engagement).where(Engagement.client_id == client_id, Engagement.fy_code == "2025-26")
    )
    assert found is not None
    return found.engagement_id


class TestValidationPage:
    def test_it_renders_with_findings(self, app_client: TestClient, engagement_id: int) -> None:
        _sign_in(app_client)
        response = app_client.get(f"/engagements/{engagement_id}/validation")
        assert response.status_code == 200
        assert "Findings" in response.text

    def test_findings_deep_link_to_the_field(
        self, app_client: TestClient, db: Session, engagement_id: int
    ) -> None:
        # §9 — "each deep-linked to the offending field".
        from app.services.engagement import set_response

        set_response(db, engagement_id, "caro.viii", "", updated_by="t")
        db.commit()
        _sign_in(app_client)
        body = app_client.get(f"/engagements/{engagement_id}/validation").text
        assert f"/engagements/{engagement_id}#field-caro.viii" in body


class TestCommentThread:
    def test_a_manager_can_raise_and_resolve(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        csrf = _sign_in(app_client, "manager@firm.local")
        raised = app_client.post(
            f"/engagements/{engagement_id}/comments",
            data={
                "csrf_token": csrf,
                "body": "Confirm the AY 2022-23 demand.",
                "field_key": "caro.vii.b.status",
            },
            follow_redirects=False,
        )
        assert raised.status_code == 303
        page = app_client.get(f"/engagements/{engagement_id}/validation").text
        assert "Confirm the AY 2022-23 demand." in page
        assert "open" in page

    def test_anyone_can_raise_a_comment(self, app_client: TestClient, engagement_id: int) -> None:
        # The manager-only gate went with the roles (Step 4a).
        csrf = _sign_in(app_client)
        response = app_client.post(
            f"/engagements/{engagement_id}/comments",
            data={"csrf_token": csrf, "body": "A review point."},
            follow_redirects=False,
        )
        assert response.status_code == 303

    def test_an_empty_comment_is_refused(self, app_client: TestClient, engagement_id: int) -> None:
        csrf = _sign_in(app_client, "manager@firm.local")
        response = app_client.post(
            f"/engagements/{engagement_id}/comments",
            data={"csrf_token": csrf, "body": "   "},
            follow_redirects=False,
        )
        assert response.status_code == 400


class TestStatusAdvancement:
    def test_open_comments_block_approval(
        self, app_client: TestClient, db: Session, engagement_id: int
    ) -> None:
        csrf = _sign_in(app_client, "manager@firm.local")
        app_client.post(
            f"/engagements/{engagement_id}/comments",
            data={"csrf_token": csrf, "body": "Unresolved point."},
            follow_redirects=False,
        )
        engagement = db.get(Engagement, engagement_id)
        # Decision 29 removed the reviewer states; Prepared is now the only
        # step before approval, and both gates sit on that move.
        engagement.status = EngagementStatus.PREPARED
        db.commit()

        csrf = _sign_in(app_client, "partner@firm.local")
        response = app_client.post(
            f"/engagements/{engagement_id}/status",
            data={"csrf_token": csrf, "target": "approved"},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "open review comment" in response.text

    def test_an_illegal_jump_is_refused(self, app_client: TestClient, engagement_id: int) -> None:
        csrf = _sign_in(app_client, "partner@firm.local")
        response = app_client.post(
            f"/engagements/{engagement_id}/status",
            data={"csrf_token": csrf, "target": "finalised"},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "Cannot move" in response.text


class TestFinalisation:
    def test_a_missing_udin_is_refused(
        self, app_client: TestClient, db: Session, engagement_id: int
    ) -> None:
        engagement = db.get(Engagement, engagement_id)
        engagement.status = EngagementStatus.APPROVED
        db.commit()
        csrf = _sign_in(app_client, "partner@firm.local")
        response = app_client.post(
            f"/engagements/{engagement_id}/finalise",
            data={"csrf_token": csrf, "udin": ""},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "UDIN" in response.text

    def test_a_partner_can_finalise_a_clean_file(
        self, app_client: TestClient, db: Session, engagement_id: int
    ) -> None:
        engagement = db.get(Engagement, engagement_id)
        engagement.status = EngagementStatus.APPROVED
        db.commit()
        csrf = _sign_in(app_client, "partner@firm.local")
        response = app_client.post(
            f"/engagements/{engagement_id}/finalise",
            data={"csrf_token": csrf, "udin": UDIN},
            follow_redirects=False,
        )
        assert response.status_code == 303
        db.expire_all()
        assert db.get(Engagement, engagement_id).status is EngagementStatus.FINALISED

    def test_anyone_can_finalise(
        self, app_client: TestClient, db: Session, engagement_id: int
    ) -> None:
        engagement = db.get(Engagement, engagement_id)
        engagement.status = EngagementStatus.APPROVED
        db.commit()
        csrf = _sign_in(app_client)
        response = app_client.post(
            f"/engagements/{engagement_id}/finalise",
            data={"csrf_token": csrf, "udin": UDIN},
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestDocumentGeneration:
    def test_generating_records_an_instance(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        csrf = _sign_in(app_client, "partner@firm.local")
        response = app_client.post(
            f"/engagements/{engagement_id}/generate/caro_2020",
            data={"csrf_token": csrf},
            follow_redirects=False,
        )
        assert response.status_code == 303
        page = app_client.get(f"/engagements/{engagement_id}/validation").text
        assert "caro_2020" in page

    def test_the_audit_pack_downloads_as_a_zip(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        csrf = _sign_in(app_client, "partner@firm.local")
        response = app_client.post(
            f"/engagements/{engagement_id}/audit-pack",
            data={"csrf_token": csrf},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert response.content[:2] == b"PK"

    def test_a_document_from_another_engagement_is_not_downloadable(
        self, app_client: TestClient, db: Session, engagement_id: int, client_id: int
    ) -> None:
        # §13 — downloads authorised per engagement, never by guessable path.
        csrf = _sign_in(app_client, "partner@firm.local")
        app_client.post(
            f"/engagements/{engagement_id}/generate/caro_2020",
            data={"csrf_token": csrf},
            follow_redirects=False,
        )
        from app.models.issuance import DocumentInstance

        instance = db.scalar(select(DocumentInstance))
        assert instance is not None
        other = db.scalar(
            select(Engagement).where(
                Engagement.client_id == client_id, Engagement.fy_code == "2024-25"
            )
        )
        response = app_client.get(
            f"/engagements/{other.engagement_id}/documents/{instance.doc_id}/download"
        )
        assert response.status_code == 404


class TestExcelRoute:
    def test_the_workbook_downloads(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        response = app_client.get("/engagements/export/workbook")
        assert response.status_code == 200
        assert response.content[:2] == b"PK"
