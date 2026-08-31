"""Enumerations shared across the schema. Build Prompt v2 §5 and §10."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    STAFF = "staff"
    MANAGER = "manager"
    PARTNER = "partner"
    ADMIN = "admin"


class CompanyType(StrEnum):
    PVT = "pvt"
    PUB_UNLISTED = "pub_unlisted"
    PUB_LISTED = "pub_listed"
    OPC = "opc"
    SMALL = "small"
    SEC8 = "sec8"
    NIDHI = "nidhi"


class Framework(StrEnum):
    IND_AS = "indas"
    IGAAP = "igaap"


class Designation(StrEnum):
    MANAGING = "managing"
    WHOLE_TIME = "whole_time"
    EXECUTIVE = "executive"
    NON_EXECUTIVE = "non_executive"
    INDEPENDENT = "independent"
    NOMINEE = "nominee"
    ADDITIONAL = "additional"


class KmpRole(StrEnum):
    CFO = "cfo"
    CEO = "ceo"
    CS = "cs"
    MANAGER = "manager"


class OpinionType(StrEnum):
    CLEAN = "clean"
    QUALIFIED = "qualified"
    ADVERSE = "adverse"
    DISCLAIMER = "disclaimer"


class GoingConcern(StrEnum):
    NONE = "none"
    EOM = "eom"
    MATERIAL_UNCERTAINTY = "material_uncertainty"


class EngagementStatus(StrEnum):
    """The §10 workflow. Order matters — see `app.core.permissions`."""

    NOT_STARTED = "not_started"
    DATA_COLLECTION = "data_collection"
    PREPARED = "prepared"
    # MANAGER_REVIEW and PARTNER_REVIEW were removed on 17 August 2026
    # (decision 29). The person who prepares the file finalises it, so a
    # separate reviewer state described a handover that never happens here.
    # The GATES they carried did not go with them -- see `app.core.permissions`.
    APPROVED = "approved"
    FINALISED = "finalised"
    ARCHIVED = "archived"


class ResponseSource(StrEnum):
    USER = "user"
    CARRIED_FORWARD = "carried_forward"
    DEFAULT = "default"
    IMPORTED = "imported"


class CommentStatus(StrEnum):
    OPEN = "open"
    RESPONDED = "responded"
    RESOLVED = "resolved"


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    FINAL = "final"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"
