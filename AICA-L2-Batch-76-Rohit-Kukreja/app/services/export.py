"""Audit pack, PDF and file storage. Build Prompt v2 §11.2 and §11.4."""

from __future__ import annotations

import json
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import ClauseSet, DocumentTemplate, IssuedBy
from app.config import PROJECT_ROOT, Settings, get_settings
from app.core.snapshot import content_hash, freeze
from app.models.engagement import Engagement
from app.models.enums import DocumentStatus
from app.models.issuance import AuditLog, DocumentInstance
from app.models.masters import Client, ClientProfile, Firm
from app.render import docx as docx_renderer
from app.render.base import Document
from app.services.applicability import applicable_flags
from app.services.document import build_document
from app.services.engagement import answer_map, child_row_dicts
from app.services.render_context import signing_context

# §11.2 — numbered, in the order a file is assembled.
PACK_ORDER: tuple[tuple[str, str], ...] = (
    ("engagement_letter", "Engagement_Letter"),
    ("mrl", "Management_Representation_Letter"),
    ("auditors_report", "Auditors_Report"),
    ("caro_2020", "CARO_2020_Annexure_A"),
    ("ifc_report", "IFC_Report_Annexure_B"),
    ("directors_report", "Directors_Report"),
)


class ExportError(RuntimeError):
    """Message is safe to show a user."""


@dataclass(frozen=True, slots=True)
class GeneratedDocument:
    doc_type: str
    version_no: int
    path: Path
    content_sha256: str
    pdf_path: Path | None = None


def issued_document(session: Session, engagement: Engagement, document_id: str) -> tuple[Path, int]:
    """The latest ISSUED .docx for one document, and its version number.

    Decision 77. The preview pane offered exactly one download -- the draft --
    and went on offering it after the year was finalised, so the firm finalised
    every report and the file that came back still read "DRAFT FOR DISCUSSION
    -- NOT AN ISSUED DOCUMENT".

    Nothing was wrong with the stamp. The draft path is *supposed* to stamp
    what it renders; the fault was offering a scratch render as the only way
    out of a finished file.
    """
    instance = session.scalars(
        select(DocumentInstance)
        .where(
            DocumentInstance.engagement_id == engagement.engagement_id,
            DocumentInstance.doc_type == document_id,
        )
        .order_by(DocumentInstance.version_no.desc())
    ).first()

    if instance is None:
        raise ExportError(
            "This document has not been generated yet. Generate it from "
            "Review & finalise — a draft is not an issued document."
        )

    path = Path(instance.docx_path)
    if not path.exists():
        raise ExportError(
            f"Version {instance.version_no} of this document was generated but its file is "
            f"no longer at {path.name}. Generate it again from Review & finalise."
        )
    return path, instance.version_no


def _safe_name(value: str) -> str:
    """Filenames derive from ids and metadata, never free text (§11.4)."""
    keep = [c if c.isalnum() else "_" for c in value]
    return "".join(keep).strip("_") or "document"


def document_dir(settings: Settings, client_code: str, fy_code: str) -> Path:
    path: Path = (
        settings.data_path / "clients" / _safe_name(client_code) / f"FY{fy_code}" / "documents"
    )
    return path


def to_pdf(source: Path) -> Path | None:
    """Convert via LibreOffice if available. Never crash (§11.2).

    Absence of `soffice` is an ordinary configuration, not an error: §1 makes
    PDF optional and requires graceful degradation to DOCX only.
    """
    settings = get_settings()
    if not settings.pdf_enabled:
        return None
    try:
        subprocess.run(  # noqa: S603
            [
                settings.soffice_path,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(source.parent),
                str(source),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    candidate = source.with_suffix(".pdf")
    return candidate if candidate.exists() else None


def generate_document(
    session: Session,
    engagement: Engagement,
    document_id: str,
    clause_set: ClauseSet,
    *,
    generated_by: str,
    with_pdf: bool = True,
) -> GeneratedDocument:
    """Render, freeze the payload, hash it and record the instance."""
    client = session.get(Client, engagement.client_id)
    profile = session.get(ClientProfile, engagement.profile_id) if engagement.profile_id else None
    if client is None:
        raise ExportError("This engagement has no client record")

    responses = answer_map(session, engagement.engagement_id)
    child_data = {
        clause.id: child_row_dicts(session, engagement.engagement_id, clause.repeating_block.entity)
        for clause in clause_set.for_document(document_id, engagement.fy_end)
        if clause.repeating_block is not None
    }
    context = signing_context(session, engagement, client, profile)

    built = build_document(
        clause_set,
        document_id,
        engagement.fy_end,
        responses=responses,
        child_rows=child_data,
        context=context,
        applicable=applicable_flags(session, engagement),
    )
    if not built.exportable:
        raise ExportError(f"{built.blocking_count} finding(s) block export of this document")

    payload = freeze(
        document_id=document_id,
        template_version=clause_set.manifest.template_version,
        responses=responses,
        child_rows=child_data,
        context=context,
    )
    digest = content_hash(built.document)

    previous = session.scalar(
        select(DocumentInstance)
        .where(
            DocumentInstance.engagement_id == engagement.engagement_id,
            DocumentInstance.doc_type == document_id,
        )
        .order_by(DocumentInstance.version_no.desc())
        .limit(1)
    )
    version_no = (previous.version_no + 1) if previous else 1

    settings = get_settings()
    target_dir = document_dir(settings, client.client_code, engagement.fy_code)
    filename = f"{engagement.engagement_id}_{_safe_name(document_id)}_v{version_no}.docx"
    path = target_dir / filename

    docx_renderer.render(
        built.document,
        path,
        client_name=profile.company_name if profile else client.client_code,
        fy_code=f"FY {engagement.fy_code}",
        generated_at=datetime.now(UTC).strftime("%d-%b-%Y %H:%M UTC"),
    )
    pdf_path = to_pdf(path) if with_pdf else None

    instance = DocumentInstance(
        engagement_id=engagement.engagement_id,
        doc_type=document_id,
        version_no=version_no,
        template_version=clause_set.manifest.template_version,
        payload_json=payload,
        content_sha256=digest,
        generated_by=generated_by,
        docx_path=str(path),
        pdf_path=str(pdf_path) if pdf_path else "",
        status=DocumentStatus.DRAFT,
    )
    session.add(instance)
    session.add(
        AuditLog(
            entity="document_instance",
            entity_id=f"{engagement.engagement_id}:{document_id}",
            action="generate",
            after_json=json.dumps({"version": version_no, "sha256": digest}),
            actor=generated_by,
        )
    )
    session.flush()

    return GeneratedDocument(
        doc_type=document_id,
        version_no=version_no,
        path=path,
        content_sha256=digest,
        pdf_path=pdf_path,
    )


def build_audit_pack(
    session: Session,
    engagement: Engagement,
    clause_set: ClauseSet,
    *,
    generated_by: str,
) -> Path:
    """Numbered document set plus manifest.json, zipped (§11.2)."""
    client = session.get(Client, engagement.client_id)
    profile = session.get(ClientProfile, engagement.profile_id) if engagement.profile_id else None
    if client is None:
        raise ExportError("This engagement has no client record")

    generated: list[tuple[int, str, GeneratedDocument]] = []
    skipped: list[str] = []

    for index, (document_id, label) in enumerate(PACK_ORDER, start=1):
        if document_id not in clause_set.documents:
            # The repository does not hold this document yet. Recording it
            # beats shipping a pack that silently lacks a statutory report.
            skipped.append(document_id)
            continue
        generated.append(
            (
                index,
                label,
                generate_document(
                    session,
                    engagement,
                    document_id,
                    clause_set,
                    generated_by=generated_by,
                ),
            )
        )

    if not generated:
        raise ExportError("No documents in this engagement could be generated")

    name = _safe_name(profile.company_name if profile else client.client_code)
    settings = get_settings()
    pack_dir = document_dir(settings, client.client_code, engagement.fy_code)
    pack_path = pack_dir / f"{name}_FY{engagement.fy_code}_Audit_Pack.zip"

    manifest = {
        "client": profile.company_name if profile else client.client_code,
        "client_code": client.client_code,
        "cin": client.cin,
        "financial_year": engagement.fy_code,
        "template_version": clause_set.manifest.template_version,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "generated_by": generated_by,
        "documents": [
            {
                "sequence": index,
                "doc_type": item.doc_type,
                "version": item.version_no,
                "filename": f"{index:02d}_{label}.docx",
                "sha256": item.content_sha256,
                "pdf": bool(item.pdf_path),
            }
            for index, label, item in generated
        ],
        "documents_not_in_repository": skipped,
        "pdf_available": settings.pdf_enabled,
    }

    with zipfile.ZipFile(pack_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for index, label, item in generated:
            archive.write(item.path, f"{index:02d}_{label}.docx")
            if item.pdf_path:
                archive.write(item.pdf_path, f"{index:02d}_{label}.pdf")
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))

    session.add(
        AuditLog(
            entity="engagement",
            entity_id=str(engagement.engagement_id),
            action="audit_pack",
            after_json=json.dumps({"documents": len(generated), "skipped": skipped}),
            actor=generated_by,
        )
    )
    session.flush()
    return pack_path


def reprint(
    session: Session, doc_id: int, clause_set: ClauseSet, target: Path
) -> tuple[Path, bool]:
    """Reprint from the stored snapshot, never from current data (§18.6).

    Returns the path and whether the reprint's hash matches what was
    recorded — the check that makes "byte-identical" verifiable rather than
    merely claimed.
    """
    instance = session.get(DocumentInstance, doc_id)
    if instance is None:
        raise ExportError("Document not found")

    from app.core.snapshot import thaw

    payload = thaw(instance.payload_json)
    engagement = session.get(Engagement, instance.engagement_id)
    if engagement is None:
        raise ExportError("The engagement for this document no longer exists")

    built = build_document(
        clause_set,
        instance.doc_type,
        engagement.fy_end,
        responses=payload["responses"],
        child_rows=payload["child_rows"],
        context=payload["context"],
    )
    docx_renderer.render(built.document, target)
    return target, content_hash(built.document) == instance.content_sha256


def rendered_from_snapshot(session: Session, doc_id: int, clause_set: ClauseSet) -> Document:
    """The node tree a stored document reproduces, without writing a file."""
    instance = session.get(DocumentInstance, doc_id)
    if instance is None:
        raise ExportError("Document not found")

    from app.core.snapshot import thaw

    payload = thaw(instance.payload_json)
    engagement = session.get(Engagement, instance.engagement_id)
    if engagement is None:
        raise ExportError("The engagement for this document no longer exists")

    return build_document(
        clause_set,
        instance.doc_type,
        engagement.fy_end,
        responses=payload["responses"],
        child_rows=payload["child_rows"],
        context=payload["context"],
    ).document


def letterhead_for(
    document: DocumentTemplate,
    firm: Firm | None,
    client: Client | None,
    profile: ClientProfile | None,
) -> docx_renderer.LetterheadBlock:
    """The letterhead this document goes out on.

    Driven by `issued_by` in the manifest, not by the document id, so a document
    added later has to state whose paper it is rather than silently inheriting
    the firm's.

    A company gets no "Chartered Accountants" subtitle and no logo --- the tool
    holds no client artwork --- and its registration line is the **CIN**, not an
    FRN. Labelling a company's CIN "FRN" is exactly the sort of thing that
    survives review because nobody reads a letterhead twice.
    """
    if document.issued_by is IssuedBy.COMPANY:
        name = (profile.company_name if profile else "") or (client.client_code if client else "")
        return docx_renderer.LetterheadBlock(
            name=name,
            subtitle="",
            lines=tuple(
                bit
                for bit in (
                    profile.registered_addr if profile else "",
                    f"CIN {client.cin}" if client and client.cin else "",
                )
                if bit
            ),
        )

    return docx_renderer.LetterheadBlock(
        name=firm.firm_name if firm else "",
        subtitle="Chartered Accountants" if firm and firm.firm_name else "",
        lines=tuple(
            bit
            for bit in (
                firm.address if firm else "",
                f"FRN {firm.frn}" if firm and firm.frn else "",
            )
            if bit
        ),
        logo_path=_logo_file(firm),
        logo_url=firm.logo_path if firm else "",
    )


def _logo_file(firm: Firm | None) -> str:
    """Resolve the stored logo to a path on disk.

    `Firm.logo_path` holds what the browser needs -- typically `/static/x.png`
    -- and a .docx needs a file. Resolved here rather than in the renderer,
    which has no business knowing how this application serves its static files.
    """
    if firm is None or not firm.logo_path:
        return ""
    stored = firm.logo_path
    if stored.startswith("/static/"):
        return str(PROJECT_ROOT / "app" / "static" / stored.removeprefix("/static/"))
    return stored


def draft_document(
    session: Session,
    engagement: Engagement,
    document_id: str,
    clause_set: ClauseSet,
    firm: Firm | None,
) -> Path:
    """Render the current preview to a .docx on the firm's letterhead.

    Partner's request, 17 August 2026: see the document on firm paper while
    still collecting data, without waiting for every finding to clear.

    **Deliberately not a `generate_document`.** Nothing is frozen, no hash is
    taken, no `DocumentInstance` is recorded and no version number is consumed:
    a draft is not an issued document and must not appear in the document
    register or the audit pack. It is written to a scratch path the caller
    streams and then forgets.

    **The export gate is bypassed on purpose, so the page has to say so.**
    Every unanswered field and unresolved placeholder still prints exactly as it
    stands, which is the point of looking. `render(..., draft=True)` stamps
    "DRAFT FOR DISCUSSION -- NOT AN ISSUED DOCUMENT" on it, and that stamp is
    the only thing standing between a half-finished file on firm letterhead and
    something that reads like a signed report.
    """
    client = session.get(Client, engagement.client_id)
    profile = session.get(ClientProfile, engagement.profile_id) if engagement.profile_id else None
    if client is None:
        raise ExportError("This engagement has no client record")

    child_data = {
        clause.id: child_row_dicts(session, engagement.engagement_id, clause.repeating_block.entity)
        for clause in clause_set.for_document(document_id, engagement.fy_end)
        if clause.repeating_block is not None
    }
    built = build_document(
        clause_set,
        document_id,
        engagement.fy_end,
        responses=answer_map(session, engagement.engagement_id),
        child_rows=child_data,
        context=signing_context(session, engagement, client, profile),
        applicable=applicable_flags(session, engagement),
    )
    if not built.has_body:
        raise ExportError(
            f"{clause_set.documents[document_id].title} has no content for this engagement — "
            "every clause in it is ruled out by applicability, so there is nothing to draft."
        )

    settings = get_settings()
    # A scratch path, kept out of the client's documents folder on purpose:
    # a draft must never sit alongside issued documents where it could be
    # picked up as one. Overwritten on every request rather than versioned.
    target = (
        settings.data_path
        / "drafts"
        / f"{engagement.engagement_id}_{_safe_name(document_id)}_draft.docx"
    )
    docx_renderer.render(
        built.document,
        target,
        client_name=profile.company_name if profile else client.client_code,
        fy_code=f"FY {engagement.fy_code}",
        generated_at=datetime.now(UTC).strftime("%d-%b-%Y %H:%M UTC"),
        letterhead=letterhead_for(clause_set.documents[document_id], firm, client, profile),
        draft=True,
    )
    return target
