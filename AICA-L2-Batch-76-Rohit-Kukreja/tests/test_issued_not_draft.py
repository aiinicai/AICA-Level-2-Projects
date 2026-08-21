"""A finalised year must not hand back a DRAFT. Decision 77.

The firm finalised every report and the file that came back still read
"DRAFT FOR DISCUSSION -- NOT AN ISSUED DOCUMENT · FY 2025-26".

Nothing was wrong with the stamp. The draft path is *supposed* to stamp what it
renders — it bypasses the export gate on purpose, so unanswered fields print as
they stand, and that stamp is the only thing between a half-finished file on
firm letterhead and something that reads like a signed report.

The fault was that the preview pane offered the draft and nothing else,
whatever state the file was in. From a finished engagement it was the only
download on the page.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engagement import Engagement
from app.models.enums import EngagementStatus
from app.services.export import ExportError, issued_document
from tests.test_client_routes import _sign_in


def _finalised(db: Session) -> Engagement:
    engagement = db.scalars(
        select(Engagement).where(Engagement.status == EngagementStatus.FINALISED)
    ).first()
    assert engagement is not None, "the fixture has no finalised year"
    return engagement


def _open_year(db: Session) -> Engagement:
    engagement = db.scalars(
        select(Engagement).where(Engagement.status != EngagementStatus.FINALISED)
    ).first()
    assert engagement is not None
    return engagement


class TestTheStampBelongsOnDraftsOnly:
    def test_the_draft_renderer_still_stamps(self) -> None:
        """Unchanged, and it must stay that way: a draft on firm letterhead
        with no stamp is indistinguishable from an issued report."""
        source = (Path("app") / "render" / "docx.py").read_text(encoding="utf-8")
        assert "DRAFT FOR DISCUSSION -- NOT AN ISSUED DOCUMENT" in source

    def test_only_the_draft_path_asks_for_it(self) -> None:
        """`generate_document` must never pass `draft=True`.

        Swept over the export service rather than asserted about one call, so a
        new export path cannot quietly stamp an issued document.
        """
        import ast

        source = (Path("app") / "services" / "export.py").read_text(encoding="utf-8")
        # Parsed, not grepped: the docstring beside the draft path quotes
        # `render(..., draft=True)` to explain itself, and a text search counts
        # the prose as a second stamping call.
        tree = ast.parse(source)
        stamped = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            for kw in node.keywords
            if kw.arg == "draft" and isinstance(kw.value, ast.Constant) and kw.value.value is True
        ]
        assert len(stamped) == 1, f"{len(stamped)} export calls stamp DRAFT; exactly one should"


class TestAFinalisedYearOffersTheIssuedDocument:
    def test_the_preview_pane_links_to_the_issued_file(
        self, app_client: TestClient, db: Session
    ) -> None:
        engagement = _finalised(db)
        _sign_in(app_client)
        body = app_client.get(f"/engagements/{engagement.engagement_id}").text
        assert f"/documents/{engagement.engagement_id}/" in body
        assert "/issued" in body, "a finalised year still offered only the draft"
        assert "Download the issued document" in body

    def test_an_open_year_still_offers_the_draft(self, app_client: TestClient, db: Session) -> None:
        """The partner asked for this on 17 August: read the document on firm
        paper while still collecting data. It must not be lost to the fix."""
        engagement = _open_year(db)
        _sign_in(app_client)
        body = app_client.get(f"/engagements/{engagement.engagement_id}").text
        assert "/draft" in body
        assert "Stamped DRAFT" in body

    def test_drafting_a_finalised_year_is_refused(
        self, app_client: TestClient, db: Session
    ) -> None:
        """Belt and braces: the link is gone, and the route says no as well.

        A URL someone bookmarked while the file was open is exactly how the
        stamped copy would come back.
        """
        engagement = _finalised(db)
        _sign_in(app_client)
        response = app_client.get(
            f"/documents/{engagement.engagement_id}/auditors_report/draft",
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "finalised" in response.text


class TestTheIssuedDocumentComesFromTheRegister:
    def test_it_refuses_when_nothing_was_generated(self, db: Session) -> None:
        """Not a fallback to the draft. A document that was never generated has
        no issued version, and saying so is the only honest answer."""
        engagement = _finalised(db)
        with pytest.raises(ExportError, match="has not been generated"):
            issued_document(db, engagement, "auditors_report")

    def test_it_serves_the_latest_version(self, db: Session, tmp_path: Path) -> None:
        from app.models.enums import DocumentStatus
        from app.models.issuance import DocumentInstance

        engagement = _finalised(db)
        for version in (1, 2):
            path = tmp_path / f"report_v{version}.docx"
            path.write_bytes(b"docx")
            db.add(
                DocumentInstance(
                    engagement_id=engagement.engagement_id,
                    doc_type="auditors_report",
                    version_no=version,
                    template_version="1.0.0-approved",
                    payload_json="{}",
                    content_sha256=f"sha{version}",
                    generated_by="tester",
                    docx_path=str(path),
                    pdf_path="",
                    status=DocumentStatus.DRAFT,
                )
            )
        db.flush()

        found, version_no = issued_document(db, engagement, "auditors_report")
        assert version_no == 2, "an older version was served"
        assert found.name == "report_v2.docx"

    def test_a_missing_file_says_so_rather_than_falling_back(
        self, db: Session, tmp_path: Path
    ) -> None:
        from app.models.enums import DocumentStatus
        from app.models.issuance import DocumentInstance

        engagement = _finalised(db)
        db.add(
            DocumentInstance(
                engagement_id=engagement.engagement_id,
                doc_type="mrl",
                version_no=1,
                template_version="1.0.0-approved",
                payload_json="{}",
                content_sha256="sha",
                generated_by="tester",
                docx_path=str(tmp_path / "gone.docx"),
                pdf_path="",
                status=DocumentStatus.DRAFT,
            )
        )
        db.flush()
        with pytest.raises(ExportError, match="no longer at"):
            issued_document(db, engagement, "mrl")
